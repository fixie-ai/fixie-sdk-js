/**
 * We're using Nodemon in a hacky way. Nodemon wants to spawn a process, but we just want to listen for the file
 * change event in the parent process. So we just give Nodemon this empty file to run.
 */
